#!/usr/bin/env python3
"""Check packed assets, native C64 expansion, coherent buffers and VIC pixels."""
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


def decode(stream):
    output, cursor, literals, matches, overlaps = bytearray(), 0, 0, 0, 0
    while stream[cursor]:
        command = stream[cursor]
        cursor += 1
        count = command & 127
        assert count
        if command & 128:
            distance = stream[cursor]
            cursor += 1
            assert 0 < distance <= len(output)
            overlaps += count > distance
            for _ in range(count):
                output.append(output[-distance])
            matches += 1
        else:
            output.extend(stream[cursor:cursor+count])
            cursor += count
            literals += 1
    return bytes(output), cursor+1, (literals, matches, overlaps)


def expected_image(raw, palette):
    pixels = []
    backgrounds = [6, 11, 0, 14]
    for y in range(200):
        for x in range(320):
            row, col, subrow = y//8, x//8, y%8
            code = (col+3*row) % 64
            font = 0x81 if (code+subrow) % 8 == 0 else (255 if subrow == 0 else 0)
            color = 14 if font & (128 >> (x%8)) else backgrounds[(row+col)%4]
            # Sprite DMA begins on the raster after its Y comparator matches.
            if 64 <= x < 256 and 50 <= y < 134:
                sx, sy = (x-64)//2, (y-50)//2
                sprite = (sy//21)*4 + sx//24
                byte = raw[sprite*64 + (sy%21)*3 + (sx%24)//8]
                if byte & (128 >> (sx%8)):
                    color = 1
            pixels.append(palette[color])
    image = Image.new("RGB", (320, 200))
    image.putdata(pixels)
    return image


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "verification.json").unlink(missing_ok=True)
    spec = importlib.util.spec_from_file_location("native_common", ROOT / "verify.py")
    common = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(common)
    labels = common.read_labels(HERE / "build/main.sym")
    program = HERE / "build/example.prg"
    data = program.read_bytes()
    load = int.from_bytes(data[:2], "little")
    raw = (HERE / "build/frames.raw").read_bytes()
    assert len(raw) == 25*512 and len({raw[i*512:(i+1)*512] for i in range(25)}) == 25
    packed_checks = []
    for phase in range(25):
        offset = labels[f"packed{phase}"]-load+2
        expanded, consumed, counts = decode(data[offset:])
        assert expanded == raw[phase*512:(phase+1)*512]
        assert not any(expanded[i*64+63] for i in range(8))
        packed_checks.append({"phase": phase, "bytes": consumed, "literal_chunks": counts[0],
                              "match_chunks": counts[1], "overlapping_matches": counts[2]})
    assert sum(p["overlapping_matches"] for p in packed_checks) > 0
    palette_path = ROOT / "palettes/colodore.vpl"
    palette = [tuple(int(v, 16) for v in line.split()[:3])
               for line in palette_path.read_text().splitlines()
               if line.strip() and not line.startswith("#")]
    with socket.socket() as reserve:
        reserve.bind(("127.0.0.1", 0))
        port = reserve.getsockname()[1]
    command = common.vice_command(shutil.which("x64sc"), program, port, palette_path)
    monitor, process, states, pictures, trace_text = None, None, [], [], []
    try:
        with (OUT / "vice.log").open("w") as log:
            process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT,
                                       start_new_session=True)
            with common.connect_monitor(process, port) as connection:
                monitor = common.Monitor(connection)
                monitor.run("r")
                monitor.run(f"break {labels['framePublished']:04x}")
                monitor.run(f"break {labels['rasterIRQ']:04x}")
                monitor.run("disable 2")
                monitor.run(f"trace exec {labels['decompressStart']:04x}")
                monitor.run(f"trace exec {labels['decompressFinished']:04x}")
                response = monitor.run("x")
                trace_text.append(response)
                for index in range(51):
                    pc, line, clock = monitor.registers()
                    assert pc == labels["framePublished"] and line < 40
                    state = monitor.memory(OUT / f"state-{index:03d}.bin", labels["ready"], labels["rasterTick"])
                    phase, front = state[4], state[3]
                    assert phase == index % 25 and front == 1-index%2
                    expected = raw[phase*512:(phase+1)*512]
                    native = monitor.memory(OUT / f"front-{index:03d}.bin", 0x2000+512*front, 0x21ff+512*front)
                    assert native == expected
                    assert monitor.memory(OUT / "pointers.bin", 0x7f8, 0x7ff) == bytes(range(0x80+8*front, 0x88+8*front))
                    monitor.run("disable 1")
                    monitor.run("enable 2")
                    trace_text.append(monitor.run("x"))
                    assert monitor.registers()[0] == labels["rasterIRQ"]
                    assert monitor.memory(OUT / "front-after-render.bin", 0x2000+512*front, 0x21ff+512*front) == expected
                    screenshot = OUT / f"field-{index:03d}.png"
                    monitor.run(f'screenshot "{screenshot}" 2')
                    image = Image.open(screenshot).convert("RGB")
                    reference = expected_image(expected, palette)
                    candidates = [(32,35), (32,36), (32,34), (31,35), (33,35)]
                    origin = next(((x,y) for x,y in candidates
                                   if ImageChops.difference(image.crop((x,y,x+320,y+200)), reference).getbbox() is None), None)
                    if origin is None:
                        reference.save(OUT / "expected-failed.png")
                        raise AssertionError(f"Native VIC screenshot mismatch at frame {index}")
                    pictures.append(image.crop((origin[0],origin[1],origin[0]+320,origin[1]+200)))
                    states.append({"index": index, "phase": phase, "front_buffer": front,
                                   "clock": clock, "raster_line": line, "screen_origin": origin,
                                   "native_pixels": 64000})
                    monitor.run("disable 2")
                    monitor.run("enable 1")
                    if index < 50:
                        trace_text.append(monitor.run("x"))
                connection.sendall(b"quit\n")
                process.wait(timeout=5)
        common.save_animation(pictures, OUT / "prepared-bubbles.gif", 40)
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
    # Both normal boundaries are traced in the actual main thread. No PC,
    # code, output or allocator state is supplied by the verifier.
    traces = "\n".join(trace_text)
    (OUT / "decompression-traces.txt").write_text(traces)
    events = [(int(pc,16), int(clock)) for pc,clock in re.findall(
        r"\.C:([0-9a-fA-F]{4})[^\n]*?\s(\d+)\n", traces)
        if int(pc,16) in (labels["decompressStart"], labels["decompressFinished"])]
    costs = [b[1]-a[1] for a,b in zip(events,events[1:])
             if a[0] == labels["decompressStart"] and b[0] == labels["decompressFinished"]]
    assert len(costs) >= 51
    intervals = [b["clock"]-a["clock"] for a,b in zip(states,states[1:])]
    proof = {"passed": True, "program_sha256": hashlib.sha256(data).hexdigest(),
             "packed_frames": packed_checks, "states": states, "publications": len(states),
             "native_pixels_checked": 64000*len(states), "native_buffer_bytes_checked": 1024*len(states),
             "decompression_clocks": costs, "publication_intervals": intervals,
             "vice_exit_code": process.returncode,
             "limits": ["Prepared host-rendered geometry; no runtime 3D calculation",
                        "Own scene and display; not original production playback or hardware proof"]}
    (OUT / "verification.json").write_text(json.dumps(proof, indent=2)+"\n")
    print(json.dumps({"passed": True, "publications": len(states), "native_pixels": proof["native_pixels_checked"],
                      "decompression_clocks": [min(costs),max(costs)], "intervals": sorted(set(intervals)),
                      "program_sha256": proof["program_sha256"]}))


if __name__ == "__main__":
    main()
