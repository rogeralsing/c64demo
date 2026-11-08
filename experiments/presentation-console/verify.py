#!/usr/bin/env python3
"""Type normal KERNAL input, compare complete UI pixels and real SID/audio output."""
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import re
import shutil
import socket
import struct
import subprocess
import wave
from PIL import Image, ImageChops

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
OUT=HERE / "build/verification"
PATTERNS=((0,4,7,12,7,4,0,7),(0,2,5,9,12,9,5,2),(0,7,0,12,0,7,2,9))
SID_WRITES=re.compile(r"#\d+ \(Trace store ([0-9a-fA-F]{4})\)[^\n]*\n"
                      r"\.C:[^\n]*?- A:([0-9a-fA-F]{2})[^\n]*\n")


def rendered(matrix,font,palette):
    image=Image.new("RGB",(320,200))
    image.putdata([palette[15 if font[matrix[(y//8)*40+x//8]*8+y%8] & (128>>(x%8)) else 0]
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
    data=program.read_bytes()
    font=(HERE / "build/font.bin").read_bytes()
    pages=(HERE / "build/pages.bin").read_bytes()
    notes=(HERE / "build/notes.bin").read_bytes()
    palette_path=ROOT / "palettes/colodore.vpl"
    palette=[tuple(int(v,16) for v in line.split()[:3]) for line in palette_path.read_text().splitlines()
             if line.strip() and not line.startswith("#")]
    with socket.socket() as reserve:
        reserve.bind(("127.0.0.1",0))
        port=reserve.getsockname()[1]
    audio=OUT / "sid-output.wav"
    audio.unlink(missing_ok=True)
    command=common.vice_command(shutil.which("x64sc"),program,port,palette_path)
    command[command.index("-sounddev")+1]="wav"
    command += ["-soundarg",str(audio),"-limitcycles","70000000"]
    process,monitor,captures,pictures,music,inputs=None,None,[],[],[],[]
    try:
        with (OUT / "vice.log").open("w") as log:
            process=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
            with common.connect_monitor(process,port) as connection:
                monitor=common.Monitor(connection)
                monitor.run("r")
                monitor.run(f"break {labels['start']:04x}")
                monitor.run("x")
                monitor.run("bank ram")
                loaded=monitor.memory(OUT / "loaded.ram",0,65535)
                load=int.from_bytes(data[:2],"little")
                assert loaded[load:load+len(data)-2]==data[2:]
                monitor.run("delete")
                monitor.run(f"break {labels['frameComplete']:04x}")
                # The following normal INC drains VICE's pending final store
                # checkpoint; stopping immediately after STA leaves it queued.
                note_boundary=labels["noteApplied"]+3
                monitor.run(f"break {note_boundary:04x}")
                monitor.run("disable 2")
                monitor.run("trace store d400 d418")
                def run(count):
                    for _ in range(count):
                        monitor.run("x")
                def feed(values):
                    values=list(values)
                    monitor.run("keybuf "+"".join(f"\\x{v:02x}" for v in values))
                    inputs.append(values)
                def send(values):
                    values=list(values)
                    feed(values)
                    run(3*len(values)+4)
                def capture(name,page,scroll=0,typed=b"",selected=0,playing=0):
                    assert monitor.registers()[0]==labels["frameComplete"]
                    monitor.run("bank ram")
                    memory=monitor.memory(OUT / f"{name}.ram",0,65535)
                    assert memory[labels["page"]]==page
                    assert memory[labels["scrollRow"]]==scroll
                    assert memory[labels["commandLength"]]==len(typed)
                    assert memory[labels["selected"]]==selected
                    assert memory[labels["playing"]]==playing
                    matrix=bytearray(pages[page*1024:(page+1)*1024])
                    if page==0:
                        matrix[21*40+2:21*40+2+len(typed)]=typed
                    if page==1:
                        for row in range(16):
                            matrix[(row+5)*40+4:(row+5)*40+36]=notes[(row+scroll)*32:(row+scroll+1)*32]
                    if page==2:
                        for row in (7,9,11):
                            matrix[row*40+1]=32
                        matrix[(7+2*selected)*40+1]=62
                    base=memory[labels["frontHi"]]*256
                    assert base in (0x3000,0x3400)
                    assert memory[base:base+1024]==matrix
                    assert memory[0x2000:0x2800]==font
                    monitor.run("bank cpu")
                    assert all((v&15)==15 for v in monitor.memory(OUT / "colors.bin",0xd800,0xdbe7))
                    path=OUT / f"{name}.png"
                    monitor.run(f'screenshot "{path}" 2')
                    image=Image.open(path).convert("RGB").crop((32,35,352,235))
                    expected=rendered(matrix,font,palette)
                    if ImageChops.difference(image,expected).getbbox():
                        expected.save(OUT / "expected-failed.png")
                        raise AssertionError(f"Native UI pixel mismatch: {name}")
                    captures.append({"name":name,"page":page,"scroll":scroll,"typed":typed.decode(),
                                     "selected":selected,"playing":playing,"pixels":64000,"screen_base":base})
                    pictures.append(image)
                run(3)
                capture("dos",0)
                send(b"EDIT\r")
                capture("viewer-top",1)
                send(b"SSS")
                capture("viewer-scroll",1,3)
                send(b"S"*52)
                capture("viewer-bottom-clamp",1,48)
                send(b"R")
                capture("viewer-reset",1)
                send(b"Q")
                capture("viewer-return",0)
                send(b"X"*20)
                capture("command-capacity",0,typed=b"X"*16)
                send([20,20,20])
                capture("command-delete",0,typed=b"X"*13)
                send([13])
                capture("unknown-command",0)
                send(b"DIR\r")
                capture("directory",3)
                send(b"QHELP\r")
                capture("help",3)
                send(b"QREAD\r")
                capture("read-alias",1)
                send(b"QSID\r")
                capture("sid-menu",2)
                for track in range(3):
                    send([32])
                    monitor.run("disable 1")
                    monitor.run("enable 2")
                    feed([49+track])
                    for step in range(9):
                        response=monitor.run("x")
                        (OUT / f"track-{track}-note-{step}.txt").write_text(response)
                        pc,line,clock=monitor.registers()
                        assert pc==note_boundary
                        monitor.run("bank ram")
                        memory=monitor.memory(OUT / "music-state.ram",0,65535)
                        note=PATTERNS[track][step%8]
                        assert memory[labels["currentNote"]]==note
                        assert memory[labels["selected"]]==track and memory[labels["playing"]]==1
                        assert memory[labels["noteIndex"]]==step%8+1
                        frequency=round(440*2**(((48+note)-69)/12)*2**24/985248)
                        actual=[(int(a,16),int(v,16)) for a,v in SID_WRITES.findall(response)]
                        expected=[(0xd400,frequency&255),(0xd401,frequency>>8)]
                        if step==0:
                            expected=[(0xd402,0),(0xd403,8),(0xd405,0x12),(0xd406,0xb4),
                                      (0xd404,(0x41,0x11,0x81)[track]),(0xd418,15)]+expected
                        assert actual==expected,(track,step,actual,expected)
                        music.append({"track":track,"step":step,"note":note,"frequency":frequency,
                                      "clock":clock,"actual_sid_stores":len(actual)})
                    monitor.run("disable 2")
                    monitor.run("enable 1")
                    run(3)
                    capture(f"track-{track}-playing",2,selected=track,playing=1)
                    send([32])
                    capture(f"track-{track}-stopped",2,selected=track)
                send(b"Q")
                capture("sound-return-dos",0,selected=2)
                connection.sendall(b"quit\n")
                process.wait(timeout=5)
        common.save_animation(pictures,OUT / "presentation-console.gif",200)
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
    for track in range(3):
        clocks=[r["clock"] for r in music if r["track"]==track]
        assert all(abs(b-a-12*19656)<128 for a,b in zip(clocks,clocks[1:]))
    with wave.open(str(audio),"rb") as wav:
        assert wav.getsampwidth()==2
        samples=struct.unpack("<"+"h"*(wav.getnframes()*wav.getnchannels()),wav.readframes(wav.getnframes()))
        audio_proof={"frames":wav.getnframes(),"sample_rate":wav.getframerate(),
                     "peak":max(abs(x) for x in samples),"rms":math.sqrt(sum(x*x for x in samples)/len(samples))}
    assert audio_proof["frames"]>48000 and audio_proof["peak"]>200 and audio_proof["rms"]>20
    proof={"passed":True,"program_sha256":hashlib.sha256(data).hexdigest(),"captures":captures,
           "native_pixels":len(captures)*64000,"keyboard_inputs":inputs,"music":music,
           "actual_note_sid_stores":sum(r["actual_sid_stores"] for r in music),"audio":audio_proof,
           "vice_exit_code":process.returncode,
           "scope":"Own mock DOS/source viewer/SID menu; normal GETIN input, coherent pages and own synthesized audio; no original UI/files/music copied"}
    (OUT / "verification.json").write_text(json.dumps(proof,indent=2)+"\n")
    print(json.dumps({"passed":True,"ui_captures":len(captures),"native_pixels":proof["native_pixels"],
                      "notes":len(music),"sid_stores":proof["actual_note_sid_stores"],"audio":audio_proof,
                      "sha256":proof["program_sha256"]}))


if __name__=="__main__":
    main()
