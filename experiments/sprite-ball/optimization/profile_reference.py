#!/usr/bin/env python3
"""Replay verified native sprite poses through the original assembled renderer.

Instruction cycles exclude VIC DMA and interrupts. Every resulting sprite byte
is checked against the independent rational coverage recorded by verify.py.
"""
import argparse
import json
from pathlib import Path
import re

from py65.devices.mpu6502 import MPU


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("experiment", type=Path)
    args = parser.parse_args()
    build = args.experiment / "build/hexagon"
    trace = json.loads((build / "verification/delta-trace.json").read_text())
    assert len(trace["frames"]) == 513, "Require the complete canonical native run"
    labels = {name: int(value, 16) for name, value in re.findall(
        r"\.label\s+(\w+)\s*=\s*\$([0-9a-fA-F]+)", (build / "main.sym").read_text())}
    memory = [0] * 65536
    program = (build / "sprite-ball.prg").read_bytes()
    load = int.from_bytes(program[:2], "little")
    memory[load:load + len(program) - 2] = program[2:]
    cpu = MPU(memory=memory)

    def call(name):
        cpu.sp = 0xff
        cpu.stPushWord(0x01ff)
        cpu.pc = labels[name]
        start = cpu.processorCycles
        instructions = 0
        while cpu.pc != 0x0200:
            cpu.step()
            instructions += 1
            if instructions > 100000:
                raise RuntimeError(f"Routine did not return: {name} at {cpu.pc:04x}")
        return cpu.processorCycles - start + 6  # Include the caller's JSR.

    for bank in (0, 1):
        initial = trace["initial_buffers"][str(bank)]
        for base in (0x0c00 + bank * 512, 0x7800 + bank * 512):
            memory[base:base+512] = initial
    frames = []
    for frame in trace["frames"]:
        bank = frame["bank"]
        memory[labels["drawBank"]] = bank
        memory[labels["metadataBase"]] = bank * 8
        memory[labels["shapeMode"]] = frame["shape_mode"]
        memory[labels["usedSprites"]] = 0
        clear = call("clearMarkers")
        slots = []
        for slot in frame["slots"]:
            if slot["face"] is None:
                slots.append({"slot": slot["slot"], "draw_cycles": 0})
                continue
            memory[labels["faceIndex"]] = slot["face"]
            memory[labels["normalDepth"]] = 255
            memory[labels["minX"]] = memory[labels["minY"]] = 0
            for index, (x, y) in enumerate(slot["vertices"]):
                memory[labels["localX"] + index] = x
                memory[labels["localY"] + index] = y
            slots.append({"slot": slot["slot"], "draw_cycles": call("drawFace")})
        assert bytes(memory[0x1800:0x1a00]) == bytes(frame["markers"]), frame["index"]
        fill = call("fillB" if bank else "fillA")
        for slot in frame["slots"]:
            for base in (0x0c00 + bank * 512, 0x7800 + bank * 512):
                actual = bytes(memory[base + slot["slot"]*64:base + slot["slot"]*64+63])
                assert actual == bytes(slot["new"]), (frame["index"], slot["slot"])
        frames.append({"index": frame["index"], "bank": bank, "clear_cycles": clear,
                       "draw_cycles": sum(slot["draw_cycles"] for slot in slots),
                       "fill_cycles": fill, "slots": slots})
    result = {"scope": "6502 instruction cycles, no VIC DMA or IRQs",
              "frames": frames, "frames_verified": len(frames),
              "sprite_bytes_verified": len(frames) * 8 * 63 * 2}
    output = build / "verification/reference-cpu-cycles.json"
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({key: value for key, value in result.items() if key != "frames"}))


if __name__ == "__main__":
    main()
