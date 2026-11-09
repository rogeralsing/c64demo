#!/usr/bin/env python3
"""Replay actual 6502 raster paths against native-verified polygon poses.

Requires py65. Does not model VIC stalls, IRQs, music, or live presentation.
The unchanged native verifier remains the cadence acceptance gate.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import statistics
from py65.devices.mpu6502 import MPU


def labels(path):
    return {name:int(value,16) for name,value in re.findall(r"\.label\s+(\w+)\s*=\s*\$([0-9a-fA-F]+)",path.read_text())}


class Runner:
    def __init__(self, directory, initial, cached):
        build=directory/"build/hexagon"
        self.symbols=labels(build/"main.sym")
        self.program=(build/"sprite-ball.prg").read_bytes()
        self.cpu=MPU()
        address=int.from_bytes(self.program[:2],"little")
        self.cpu.memory[address:address+len(self.program)-2]=self.program[2:]
        self.cpu.p=0x20
        self.cached=cached
        self.memory=self.cpu.memory
        if cached:
            self.call("cacheInit")
        for bank in range(2):
            for base in (0x0c00+bank*512,0x7800+bank*512):
                self.memory[base:base+512]=initial[str(bank)]

    def put(self,name,value):
        self.memory[self.symbols[name]]=value

    def call(self,name):
        cpu=self.cpu
        cpu.sp=0xfd
        cpu.memory[0x1fe]=0xff
        cpu.memory[0x1ff]=0x02
        cpu.pc=self.symbols[name]
        before=cpu.processorCycles
        steps=0
        while cpu.pc!=0x0300:
            cpu.step()
            steps+=1
            if steps>100000:
                raise RuntimeError(f"6502 call did not return: {name} at {cpu.pc:04x}")
        return cpu.processorCycles-before+6

    def frame(self,frame):
        bank=frame["bank"]
        self.put("metadataBase",bank*8)
        self.put("usedSprites",0)
        self.put("shapeMode",frame["shape_mode"])
        cycles=0 if self.cached else self.call("clearMarkers")
        for slot in frame["slots"]:
            if slot["face"] is None:
                continue
            self.put("faceIndex",slot["face"])
            self.put("normalDepth",255)
            self.put("minX",0)
            self.put("minY",0)
            for i in range(6):
                point=slot["vertices"][i] if i<len(slot["vertices"]) else (0,0)
                self.memory[self.symbols["localX"]+i]=point[0]
                self.memory[self.symbols["localY"]+i]=point[1]
            cycles+=self.call("drawFace")
        if self.cached:
            cycles+=self.call("cacheClearUnused")
        cycles+=self.call("fillB" if bank else "fillA")
        for slot in frame["slots"]:
            for base in (0x0c00+bank*512,0x7800+bank*512):
                actual=self.memory[base+slot["slot"]*64:base+slot["slot"]*64+63]
                if actual!=slot["new"]:
                    raise AssertionError(f"Exact output mismatch frame {frame['index']} slot {slot['slot']} cached={self.cached}")
        dirty=self.memory[0x200+bank*8:0x208+bank*8] if self.cached else [1]*8
        return cycles,dirty


def distribution(values):
    return {"minimum":min(values),"mean":statistics.mean(values),"maximum":max(values)}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    here=Path(__file__).resolve().parent
    parser.add_argument("--baseline",type=Path,required=True)
    parser.add_argument("--candidate",type=Path,default=here)
    parser.add_argument("--trace",type=Path,required=True)
    parser.add_argument("--output",type=Path,default=here/"cache-replay.json")
    parser.add_argument("--min-frames",type=int,default=513)
    args=parser.parse_args()
    raw=args.trace.read_bytes()
    trace=json.loads(raw)
    assert len(trace["frames"])>=args.min_frames,"Canonical trace is incomplete"
    baseline=Runner(args.baseline,trace["initial_buffers"],False)
    cached=Runner(args.candidate,trace["initial_buffers"],True)
    samples=[]
    for frame in trace["frames"]:
        base_cycles,_=baseline.frame(frame)
        cache_cycles,dirty=cached.frame(frame)
        count=sum(slot["face"] is not None for slot in frame["slots"])
        samples.append({"index":frame["index"],"motion_phase":frame["index"]%256,
                        "bank":frame["bank"],"shape_mode":frame["shape_mode"],
                        "active_slots":count,"active_hits":sum(not bit for bit in dirty[:count]),
                        "unchanged_empty_slots":sum(not bit for bit in dirty[count:]),
                        "baseline_raster_cpu_cycles":base_cycles,"cache_raster_cpu_cycles":cache_cycles,
                        "cycle_change":cache_cycles-base_cycles})
    # First two renders synchronize previously unknown intro cache history.
    measured=samples[2:]
    groups={}
    for name,selected in (("all",measured),
                          ("both_axes_slow",[s for s in measured if s["motion_phase"]<64 or s["motion_phase"]>=224]),
                          ("other_phases",[s for s in measured if 64<=s["motion_phase"]<224])):
        groups[name]={"frames":len(selected),
                      "baseline_raster_cpu_cycles":distribution([s["baseline_raster_cpu_cycles"] for s in selected]),
                      "cache_raster_cpu_cycles":distribution([s["cache_raster_cpu_cycles"] for s in selected]),
                      "cycle_change":distribution([s["cycle_change"] for s in selected]),
                      "active_hits":sum(s["active_hits"] for s in selected),
                      "active_slots":sum(s["active_slots"] for s in selected),
                      "frames_faster":sum(s["cycle_change"]<0 for s in selected)}
    result={"strategy":"exact-local-shape-cache", "measurement":"assembled_6502_cpu_replay",
            "trace_sha256":hashlib.sha256(raw).hexdigest(),"trace_frames":len(samples),
            "baseline_prg_sha256":hashlib.sha256(baseline.program).hexdigest(),
            "cache_prg_sha256":hashlib.sha256(cached.program).hexdigest(),
            "exact_sprite_bytes_checked":len(samples)*8*63*2*2,
            "excluded_warmup_frames":2,"scope":"Clear/edge draw/fill and cache bookkeeping. Geometry, VIC DMA, IRQ/music excluded.",
            "groups":groups,"samples":samples}
    args.output.write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps({key:value for key,value in result.items() if key!="samples"},indent=2))


if __name__=="__main__":
    main()
