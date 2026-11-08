#!/usr/bin/env python3
"""Check deterministic audio control and bounded live stack/font behavior."""

import array
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import socket
import subprocess
import wave

from PIL import Image


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUTPUT = HERE / "build/verification"
MELODY = (0x08B4, 0x09C4, 0x0AF6, 0x0D09, 0x0EA1, 0x1168, 0x1388, 0x15EC)
BASS = (0x045A, 0x0684, 0x0750, 0x05D0)
INITIAL_SID = bytes((0xC4, 9, 0x41, 0x0A, 0x41, 0x25, 0x88,
                     0x84, 6, 0, 8, 0x11, 8, 0x88,
                     0, 0x30, 0, 8, 0x80, 5, 0, 0, 0, 0, 15))
TRACE = re.compile(r"#\d+ \(Trace store ([0-9a-f]{4})\)[^\n]*\n"
                   r"\.C:([0-9a-f]{4})[^\n]* A:([0-9a-f]{2}) X:([0-9a-f]{2})", re.I)


def advance(frame, state, sid):
    """Music contract from mathematical state, not captured output or CPU replay."""
    sid = bytearray(sid)
    if frame % 8 == 0:
        state = (state // 2) ^ (0xB8 if state % 2 else 0)
        pitch = MELODY[state % 8]
        sid[0:2] = pitch.to_bytes(2, "little")
        sid[4], sid[18] = 0x40, 0x81
        sid[15] = 0x20 + ((frame // 8) % 16)
    else:
        sid[4], sid[18] = 0x41, 0x80
    if frame % 32 == 0:
        sid[7:9] = BASS[state % 4].to_bytes(2, "little")
    sid[2], sid[3] = state, 8 | (state // 32)
    palette = bytes((8 | (state % 8), 8 | ((state // 8) % 8),
                     8 | (state // 32), 8 | ((state ^ frame) % 8)))
    return state, sid, palette


def registers(monitor):
    text = monitor.run("r")
    match = re.search(r"^\.;([0-9a-f]{4})\s+(.*)$", text, re.I | re.M)
    fields = match[2].split()
    return {"pc": int(match[1], 16), "a": int(fields[0], 16),
            "sp": int(fields[3], 16), "clock": int(fields[-1]),
            "raster": int(fields[-3])}


def checkpoint_number(response):
    return int(re.search(r"(?:BREAK|TRACE):\s*(\d+)", response)[1])


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / "receipt.json").unlink(missing_ok=True)
    spec = importlib.util.spec_from_file_location("shared_native_monitor", ROOT / "verify.py")
    shared = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(shared)
    labels = shared.read_labels(HERE / "build/main.sym")
    with socket.socket() as reservation:
        reservation.bind(("127.0.0.1", 0))
        port = reservation.getsockname()[1]
    command = shared.vice_command(os.environ.get("VICE", "x64sc"), HERE / "build/example.prg",
                                  port, ROOT / "palettes/colodore.vpl")
    audio = OUTPUT / "sid-output.wav"
    if audio.exists():
        audio.unlink()
    # WAV is the primary output backend: dummy reports zero output channels on
    # this VICE build and cannot supply a meaningful secondary recording stream.
    command[command.index("-sounddev") + 1] = "wav"
    command += ["-soundarg", str(audio)]
    monitor = None
    closed_cleanly = False
    with (OUTPUT / "vice.log").open("w") as log:
        process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT)
        try:
            with shared.connect_monitor(process, port) as connection:
                monitor = shared.Monitor(connection)
                monitor.run("r")
                irq_break = checkpoint_number(monitor.run(f"break {labels['frameComplete']:04x}"))
                monitor.run("x")
                state, sid = 0x41, bytearray(INITIAL_SID)
                frames, captures, clocks = [], [], []
                traced_writes = 0
                trace_number = None
                for frame in range(1, 257):
                    response = monitor.run("x") if frame > 1 else ""
                    state, sid, palette = advance(frame, state, sid)
                    cpu = registers(monitor)
                    clocks.append(cpu["clock"])
                    monitor.run("bank ram")
                    ram = monitor.memory(OUTPUT / "latest-ram.bin", 0, 0xFFFF)
                    monitor.run("bank cpu")
                    assert int.from_bytes(ram[labels["frameCounter"]:labels["frameCounter"] + 2], "little") == frame
                    assert ram[labels["lfsr"]] == state
                    assert ram[labels["noteCounter"]] == frame // 8
                    assert ram[labels["sidShadow"]:labels["sidShadow"] + 25] == sid
                    assert ram[labels["paletteShadow"]:labels["paletteShadow"] + 4] == palette
                    assert all(code & 0x20 for code in ram[0x0400:0x07E8])
                    if frame > 1:
                        writes = [(int(address, 16), int(value, 16))
                                  for address, pc, value, x in TRACE.findall(response)
                                  if int(pc, 16) == labels["sidStore"]
                                  and int(address, 16) == 0xD400 + int(x, 16)]
                        assert writes == [(0xD400 + index, sid[index]) for index in range(24, -1, -1)], (frame, writes)
                        traced_writes += len(writes)
                    record = {"frame": frame, "lfsr": state, "notes": frame // 8,
                              "clock": cpu["clock"], "raster": cpu["raster"],
                              "palette": list(palette), "melody_frequency_word": sid[0] + 256 * sid[1],
                              "melody_gate": sid[4] & 1, "drum_gate": sid[18] & 1}
                    if frame in (16, 64, 128, 256):
                        vic = monitor.memory(OUTPUT / "vic.bin", 0xD000, 0xD03F)
                        assert vic[0x11] & 0x7F == 0x5B and vic[0x18] & 0xFE == 0x10
                        assert bytes(value & 15 for value in vic[0x21:0x25]) == palette
                        colors = monitor.memory(OUTPUT / "colors.bin", 0xD800, 0xDBE7)
                        assert all(value & 15 == 0 for value in colors)
                        screenshot = OUTPUT / f"frame-{frame:03d}.png"
                        monitor.run(f'scrsh "{screenshot}" 2')
                        image = Image.open(screenshot).convert("RGB")
                        assert len(image.getcolors(maxcolors=1000000)) >= 3
                        captures.append(image)
                        record["screenshot"] = screenshot.name
                        (OUTPUT / f"ram-frame-{frame:03d}.bin").write_bytes(ram)
                    frames.append(record)
                    if frame == 1:
                        trace_number = checkpoint_number(monitor.run("trace store d400 d418"))
                monitor.run(f"delete {trace_number}")
                monitor.run(f"disable {irq_break}")
                push_break = checkpoint_number(monitor.run(f"break {labels['beforeFontPush']:04x}"))
                monitor.run("x")
                pushed_addresses, push_samples = set(), []
                for index in range(256):
                    if index:
                        monitor.run("x")
                    before = registers(monitor)
                    samples = monitor.memory(OUTPUT / "font-inputs.bin", labels["timerSample"], labels["lfsrSample"])
                    stack_before = monitor.memory(OUTPUT / "stack-before.bin", 0x0100, 0x01FF)
                    expected = (samples[0] ^ samples[2]) | samples[1]
                    assert before["a"] == expected
                    monitor.run("z")
                    after = registers(monitor)
                    stack_after = monitor.memory(OUTPUT / "stack-after.bin", 0x0100, 0x01FF)
                    predicted = bytearray(stack_before)
                    predicted[before["sp"]] = expected
                    assert stack_after == predicted
                    assert after["pc"] == labels["afterFontPush"]
                    assert after["sp"] == (before["sp"] - 1) % 256
                    pushed_addresses.add(before["sp"])
                    if index in (0, 63, 127, 191, 255):
                        push_samples.append({"index": index, "address": 0x0100 + before["sp"],
                                             "timer": samples[0], "envelope": samples[1],
                                             "sampled_lfsr": samples[2], "font_byte": expected,
                                             "sp_before": before["sp"], "sp_after": after["sp"]})
                assert len(pushed_addresses) == 256
                assert len({image.tobytes() for image in captures}) == len(captures)
                captures[0].save(OUTPUT / "feedback.gif", save_all=True,
                                 append_images=captures[1:], duration=500, loop=0)
                monitor.transcript.append("quit")
                connection.sendall(b"quit\n")
                process.wait(timeout=5)
                closed_cleanly = True
                receipt = {"pass": True, "irq_frames": 256, "lfsr_note_updates": 32,
                           "actual_SID_store_values_checked": traced_writes,
                           "consecutive_PHA_checks": 256, "distinct_stack_font_addresses": 256,
                           "native_IRQ_intervals_clocks": sorted(set(b - a for a, b in zip(clocks, clocks[1:]))),
                           "mean_IRQ_interval_clocks": (clocks[-1] - clocks[0]) / (len(clocks) - 1),
                           "visible_captures": len(captures), "frames": frames,
                           "font_push_samples": push_samples, "command": command,
                           "program_sha256": hashlib.sha256((HERE / "build/example.prg").read_bytes()).hexdigest(),
                           "scope": "Independent LFSR/melody/pulse/drum/palette model; actual SID write traces; live-input PHA arithmetic, all256 cyclic stack addresses and changing ECM screenshots. No full dynamic visual or analog audio oracle."}
                with wave.open(str(audio), "rb") as recording:
                    assert recording.getsampwidth() == 2
                    pcm = array.array("h", recording.readframes(recording.getnframes()))
                    peak = max(abs(value) for value in pcm)
                    rms = math.sqrt(sum(value * value for value in pcm) / len(pcm))
                    assert peak > 300 and rms > 30, (peak, rms)
                    receipt["recorded_audio"] = {"file": audio.name, "frames": recording.getnframes(),
                                                 "sample_rate": recording.getframerate(), "peak": peak,
                                                 "rms": round(rms, 2)}
                (OUTPUT / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
                print(json.dumps({key: value for key, value in receipt.items()
                                  if key not in ("frames", "command")}, indent=2))
        finally:
            if monitor:
                (OUTPUT / "monitor.log").write_text("\n".join(monitor.transcript))
            if not closed_cleanly:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)


if __name__ == "__main__":
    main()
