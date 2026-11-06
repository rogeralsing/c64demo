#!/usr/bin/env python3
"""Measure real PAL C64 renderer costs using the normal PRG and VICE debug symbols."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import socket
import statistics
import subprocess

from verify import Monitor, connect_monitor, read_labels, vice_command


STAGES = ["nextFrame", "rotateCube", "projectCube", "drawCube", "frameReady", "framePresented"]
COSTS = ["clear_and_setup", "rotation", "projection", "line_drawing", "presentation_wait"]


def profile(program, labels_file, output, executable, frames, meter=False):
    labels = read_labels(labels_file)
    stages, cost_names = list(STAGES), list(COSTS)
    if "cullFaces" in labels:
        stages.insert(stages.index("drawCube"), "cullFaces")
        cost_names.insert(cost_names.index("line_drawing"), "face_culling")
    if set(stages) - labels.keys():
        raise ValueError(f"Missing renderer debug symbols: {sorted(set(stages) - labels.keys())}")
    original = program.read_bytes()
    output.mkdir(parents=True, exist_ok=True)
    (output / "profile.json").unlink(missing_ok=True)
    palette = Path(__file__).resolve().parent / "palettes/colodore.vpl"
    with socket.socket() as reserve:
        reserve.bind(("127.0.0.1", 0))
        port = reserve.getsockname()[1]
    samples, monitor = [], None
    with (output / "vice.log").open("w") as log:
        process = subprocess.Popen(vice_command(executable, program, port, palette),
                                   stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        try:
            with connect_monitor(process, port) as connection:
                monitor = Monitor(connection)
                monitor.run("r")
                checkpoints = {}
                for stage in stages:
                    response = monitor.run(f"break {labels[stage]:04x}")
                    checkpoint = re.search(r"BREAK:\s*(\d+)", response)
                    if not checkpoint:
                        raise RuntimeError(f"Could not identify breakpoint: {response}")
                    checkpoints[stage] = int(checkpoint[1])
                for index in range(frames):
                    timings, lines = [], []
                    for stage in stages:
                        monitor.run("x")
                        pc, line, cycles = monitor.registers()
                        if pc != labels[stage]:
                            raise AssertionError(f"Expected {stage} at ${labels[stage]:04x}, stopped at ${pc:04x}.")
                        timings.append(cycles)
                        lines.append(line)
                        if meter and stage in ("rotateCube", "frameReady"):
                            response = monitor.run("m d020 d020")
                            border = re.search(r">C:d020\s+([0-9a-fA-F]{2})", response, re.I)
                            if not border:
                                raise RuntimeError(f"Could not read border color: {response}")
                            expected = 1 if stage == "rotateCube" else 0
                            if int(border[1], 16) & 15 != expected:
                                raise AssertionError(f"Border CPU meter has wrong color at {stage}.")
                        if stage == "frameReady":
                            # This label is also the busy-wait loop's back edge.
                            monitor.run(f"disable {checkpoints[stage]}")
                    monitor.run(f"enable {checkpoints['frameReady']}")
                    costs = dict(zip(cost_names, [b - a for a, b in zip(timings, timings[1:])]))
                    costs["renderer_total"] = timings[stages.index("frameReady")] - timings[0]
                    costs["total_including_wait"] = timings[-1] - timings[0]
                    samples.append({"frame": index, "costs": costs, "stage_raster_lines": lines})
            summary = {name: {"min": min(values), "max": max(values),
                              "mean": round(statistics.mean(values), 2),
                              "median": statistics.median(values)}
                       for name in [*cost_names, "renderer_total", "total_including_wait"]
                       for values in [[sample["costs"][name] for sample in samples]]}
            report = {"program_sha256": hashlib.sha256(original).hexdigest(), "pal": True,
                      "frames_profiled": frames, "pal_frame_cycles": 63 * 312,
                      "measurement": "VICE cycle counter includes VIC-II bus stalls and raster IRQs",
                      "border_cpu_meter_verified": meter,
                      "stage_boundaries": stages, "summary_cycles": summary, "samples": samples}
            (output / "profile.json").write_text(json.dumps(report, indent=2) + "\n")
            print(json.dumps({key: value for key, value in report.items() if key != "samples"}, indent=2))
        finally:
            if monitor:
                (output / "monitor.log").write_text("\n".join(monitor.transcript))
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)


if __name__ == "__main__":
    here = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("program", type=Path, nargs="?", default=here / "build/vector-cube.prg")
    parser.add_argument("--labels", type=Path, default=here / "build/cube.sym")
    parser.add_argument("--output", type=Path, default=here / "build/profile")
    parser.add_argument("--vice", default=os.environ.get("VICE") or shutil.which("x64sc"))
    parser.add_argument("--frames", type=int, default=512)
    parser.add_argument("--meter", action="store_true",
                        help="Check white border during rendering and black border while waiting.")
    args = parser.parse_args()
    if not args.vice:
        parser.error("x64sc is missing; install VICE or pass --vice /path/to/x64sc.")
    if args.frames < 1:
        parser.error("--frames must be positive.")
    profile(args.program.resolve(), args.labels.resolve(), args.output.resolve(), args.vice, args.frames, args.meter)
