#!/usr/bin/env python3
"""Compare prepared polygons with native expanded-sprite canvas output."""

import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import socket
import subprocess

from PIL import Image, ImageChops


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUTPUT = HERE / "build/verification"
BAYER = ((0, 8, 2, 10), (12, 4, 14, 6), (3, 11, 1, 9), (15, 7, 13, 5))
TRACE = re.compile(r"#\d+ \(Trace store ([0-9a-f]{4})\)\s+(\d+)/[^\n]*\n"
                   r"\.C:[^\n]*\bSTA\b[^\n]* A:([0-9a-f]{2})", re.I)


def reference(pose):
    """Direct integer half-plane tests and density thresholds, without DDA replay."""
    shift = math.floor(3 * math.sin(pose * math.tau / 16) + 0.5)
    triangles = ((72 + shift, 18, 4 + shift, 62, 140 + shift, pose),
                 (40 - shift, 24, 18 - shift, 54, 62 - shift, (pose + 8) % 16))
    pixels = []
    for y in range(63):
        for x in range(144):
            rank = BAYER[y % 4][x % 4]
            visible = False
            for material in range(16):
                left, top = 4 + 34 * (material % 4), 4 * (material // 4)
                visible |= left <= x < left + 30 and top <= y < top + 3 and rank < material
            for apex, top, left, bottom, right, material in triangles:
                height, offset = bottom - top, y - top
                visible |= (top <= y < bottom and rank < material
                            and x * height >= apex * height + (left - apex) * offset
                            and x * height < apex * height + (right - apex) * offset)
            pixels.append(visible)
    data = bytearray(1152)
    for y in range(63):
        for x in range(144):
            if pixels[y * 144 + x]:
                address = (y // 21) * 384 + (x // 24) * 64 + (y % 21) * 3 + (x % 24) // 8
                data[address] |= 0x80 >> (x % 8)
    image = Image.new("RGB", (288, 126))
    image.putdata([(0x91, 0xFF, 0x84) if pixels[(y // 2) * 144 + x // 2] else (0, 0, 0)
                   for y in range(126) for x in range(288)])
    return bytes(data), image


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / "receipt.json").unlink(missing_ok=True)
    spec = importlib.util.spec_from_file_location("shared_native_monitor", ROOT / "verify.py")
    shared = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(shared)
    labels = shared.read_labels(HERE / "build/main.sym")
    references = [reference(pose) for pose in range(16)]
    with socket.socket() as reservation:
        reservation.bind(("127.0.0.1", 0))
        port = reservation.getsockname()[1]
    command = shared.vice_command(os.environ.get("VICE", "x64sc"), HERE / "build/example.prg",
                                  port, ROOT / "palettes/colodore.vpl")
    monitor = None
    with (OUTPUT / "vice.log").open("w") as log:
        process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT)
        try:
            with shared.connect_monitor(process, port) as connection:
                monitor = shared.Monitor(connection)
                monitor.run("r")
                monitor.run(f"break {labels['displayFrameComplete']:04x}")
                monitor.run("x")
                frames, updates, images, poses = [], [], [], set()
                last_publication = None
                hidden_ready_checks = 0
                display_store_checks = 0
                y_store_checks = 0
                for field in range(1, 2001):
                    response = monitor.run("x") if field > 1 else ""
                    _, raster, clock = monitor.registers()
                    monitor.run("bank ram")
                    ram = monitor.memory(OUTPUT / "latest-ram.bin", 0, 0xFFFF)
                    monitor.run("bank cpu")
                    pose, buffer = ram[labels["frontPose"]], ram[labels["frontBuffer"]]
                    publication = int.from_bytes(ram[labels["publicationCounter"]:labels["publicationCounter"] + 2], "little")
                    frame = int.from_bytes(ram[labels["frameCounter"]:labels["frameCounter"] + 2], "little")
                    assert frame == field
                    assert pose == publication % 16 and buffer == publication % 2
                    base = 0x2000 + buffer * 0x800
                    expected, patch = references[pose]
                    actual = ram[base:base + 1152]
                    assert actual == expected, (field, pose, "front canvas bytes")
                    for which in range(2):
                        for band in range(3):
                            table = ((0x0400, 0x0800, 0x0C00),
                                     (0x3000, 0x3400, 0x3C00))[which][band] + 0x3F8
                            assert ram[table:table + 6] == bytes(range(0x80 + which * 0x20 + band * 6,
                                                                    0x86 + which * 0x20 + band * 6))
                    for page in (0x0400, 0x0800, 0x0C00, 0x3000, 0x3400, 0x3C00):
                        assert ram[page:page + 1000] == bytes(1000)
                    assert ram[0x3800:0x3808] == bytes(8)
                    if ram[labels["renderReady"]]:
                        pending = ram[labels["pendingPose"]]
                        assert pending == (publication + 1) % 16
                        hidden = 0x2000 + (buffer ^ 1) * 0x800
                        assert ram[hidden:hidden + 1152] == references[pending][0]
                        hidden_ready_checks += 1
                    vic = monitor.memory(OUTPUT / "vic.bin", 0xD000, 0xD03F)
                    assert vic[0x15] == vic[0x17] == vic[0x1D] == 0x3F
                    assert vic[0x1B] == vic[0x1C] == 0 and vic[0x10] == 0x20
                    assert vic[0x11] & 0x7F == 0x18 and vic[0x18] & 0xFE == (0xFE if buffer else 0x3E)
                    assert all(vic[0x27 + sprite] & 15 == 13 for sprite in range(6))
                    assert all(vic[2 * sprite + 1] == 148 for sprite in range(6))
                    if field > 1:
                        events = [(int(address, 16), int(line), int(value, 16))
                                  for address, line, value in TRACE.findall(response)]
                        selectors = [event for event in events if event[0] == 0xD018]
                        selection_values = (0xCE, 0xDE, 0xFE) if buffer else (0x1E, 0x2E, 0x3E)
                        assert [(address, value) for address, line, value in selectors] == [
                            (0xD018, value) for value in selection_values]
                        assert selectors[1][1] == 106 and selectors[2][1] == 148, selectors
                        y_events = [event for event in events if 0xD001 <= event[0] <= 0xD00B and event[0] % 2]
                        assert [(address, value) for address, line, value in y_events] == [
                            (0xD001 + 2 * sprite, y) for y in (64, 106, 148) for sprite in range(6)]
                        display_store_checks += len(selectors)
                        y_store_checks += len(y_events)
                    record = {"frame": field, "clock": clock, "raster": raster,
                              "publication": publication, "pose": pose, "front_buffer": buffer}
                    if publication != last_publication:
                        filename = f"publication-{publication:03d}-pose-{pose:02d}.png"
                        monitor.run(f'scrsh "{OUTPUT / filename}" 2')
                        image = Image.open(OUTPUT / filename).convert("RGB")
                        canvas = Image.new("RGB", image.size, (0, 0, 0))
                        canvas.paste(patch, (48, 49))
                        difference = ImageChops.difference(image, canvas)
                        if difference.getbbox() is not None:
                            canvas.save(OUTPUT / "expected-failed.png")
                            difference.save(OUTPUT / "difference-failed.png")
                            raise AssertionError((field, pose, "expanded sprite pixels, including band seams"))
                        (OUTPUT / f"canvas-{publication:03d}.bin").write_bytes(actual)
                        record["screenshot"] = filename
                        images.append(image)
                        updates.append(record.copy())
                        poses.add(pose)
                        last_publication = publication
                    frames.append(record)
                    if field == 1:
                        monitor.run("trace store d018")
                        monitor.run("trace store d001 d00b")
                    if publication >= 32:
                        break
                else:
                    raise AssertionError("Renderer did not publish two complete pose cycles in 2000 PAL fields")
                assert poses == set(range(16)) and hidden_ready_checks > 0
                images[0].save(OUTPUT / "sprite-vectors.gif", save_all=True,
                               append_images=images[1:], duration=120, loop=0)
                intervals = [b["frame"] - a["frame"] for a, b in zip(updates, updates[1:])]
                receipt = {"pass": True, "PAL_fields_checked": len(frames),
                           "complete_canvas_bytes_per_field": 1152, "distinct_prepared_poses": 16,
                           "published_updates_after_initial": updates[-1]["publication"],
                           "pixel_compared_publications": len(images),
                           "physical_image_dimensions": [288, 126], "logical_canvas_dimensions": [144, 63],
                           "hidden_ready_buffer_checks": hidden_ready_checks,
                           "actual_D018_stores_checked": display_store_checks,
                           "actual_sprite_Y_stores_checked": y_store_checks,
                           "PAL_fields_per_publication": intervals,
                           "mean_PAL_fields_per_publication": sum(intervals) / len(intervals),
                           "updates": updates, "frames": frames, "command": command,
                           "program_sha256": hashlib.sha256((HERE / "build/example.prg").read_bytes()).hexdigest(),
                           "scope": "Independent integer half-plane coverage and16-level density oracle; all1152 sprite buffer bytes at every field,32 publications with full expanded-DMA screenshots and all band seams, ready-buffer checks and actual display selector/Y traces. Prepared flat-bottom triangles and span runs only; no live3D/original164-pose or physical-hardware claim."}
                (OUTPUT / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
                print(json.dumps({key: value for key, value in receipt.items()
                                  if key not in ("updates", "frames", "command")}, indent=2))
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
