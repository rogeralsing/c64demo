#!/usr/bin/env python3
"""Check the native scene counter, hundred-frame waits and visible output."""

import hashlib
import importlib.util
import json
from pathlib import Path
import socket
import subprocess


ROOT = Path(__file__).resolve().parents[2]
EXAMPLE = Path(__file__).resolve().parent
OUTPUT = EXAMPLE / "build/verification"


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / "receipt.json").unlink(missing_ok=True)
    spec = importlib.util.spec_from_file_location("cube_verify", ROOT / "verify.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    labels = module.read_labels(EXAMPLE / "build/main.sym")
    with socket.socket() as reservation:
        reservation.bind(("127.0.0.1", 0))
        port = reservation.getsockname()[1]
    command = ["x64sc", "-default", "+saveres", "-minimized", "-pal", "-speed", "100",
               "+warp", "+autostart-warp", "+confirmonexit", "-sounddev", "dummy",
               "+refreshonbreak", "+binarymonitor", "-autostartprgmode", "1",
               "-autostart", str(EXAMPLE / "build/example.prg"), "-VICIIfilter", "0",
               "-remotemonitor", "-remotemonitoraddress", f"ip4://127.0.0.1:{port}"]
    monitor = None
    with (OUTPUT / "vice.log").open("w") as log:
        process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT)
        try:
            with module.connect_monitor(process, port) as connection:
                monitor = module.Monitor(connection)
                monitor.run("r")
                monitor.run(f"break {labels['frameComplete']:04x}")
                monitor.run("x")
                samples, captures = [], []
                for frame in range(1, 206):
                    if frame > 1:
                        monitor.run("x")
                    state = monitor.memory(OUTPUT / "state.bin", labels["sceneTicks"],
                                           labels["frameCounter"] + 1)
                    expected_phase = ((frame - 1) // 100) % 2
                    assert state[1] == expected_phase, (frame, list(state), expected_phase)
                    assert int.from_bytes(state[2:4], "little") == frame, (frame, list(state))
                    if frame in (1, 2, 100, 101, 102, 200, 201, 205):
                        vic = monitor.memory(OUTPUT / "vic.bin", 0xD000, 0xD03F)
                        background, border = vic[0x21] & 15, vic[0x20] & 15
                        assert background == (5 if expected_phase == 0 else 6), (frame, background)
                        assert border == 4, (frame, border)
                        screen = monitor.memory(OUTPUT / "screen.bin", 0x0400, 0x07E7)
                        assert screen[10 * 40 + 10] == 0x31 + expected_phase
                        record = {"frame": frame, "phase": expected_phase,
                                  "ticks_remaining": state[0], "background": background,
                                  "border": border}
                        if frame in (2, 102, 205):
                            screenshot = OUTPUT / f"scene-{frame:03d}.png"
                            monitor.run(f'scrsh "{screenshot}" 2')
                            image = module.Image.open(screenshot).convert("RGB")
                            record["screenshot"] = screenshot.name
                            record["distinct_colors"] = len(image.getcolors(maxcolors=1000000))
                            assert record["distinct_colors"] >= 6, record
                            captures.append(image)
                        samples.append(record)
                assert captures[0].tobytes() != captures[1].tobytes()
                captures[0].save(OUTPUT / "scenes.gif", save_all=True,
                                 append_images=captures[1:], duration=1000, loop=0)
                receipt = {"pass": True, "frames_checked": 205, "scene_period_frames": 100,
                           "expected_phases": ["green", "blue", "green"], "samples": samples,
                           "program_sha256": hashlib.sha256((EXAMPLE / "build/example.prg").read_bytes()).hexdigest(),
                           "command": command,
                           "scope": "Native PAL scene countdown, frame counter, scene digit and sampled VIC colors. Screenshots show changed visible output; no per-cycle raster timing proof."}
                (OUTPUT / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
                print(json.dumps(receipt, indent=2))
        finally:
            if monitor:
                (OUTPUT / "monitor.log").write_text("\n".join(monitor.transcript))
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


if __name__ == "__main__":
    main()
