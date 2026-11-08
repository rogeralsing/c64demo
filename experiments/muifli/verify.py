#!/usr/bin/env python3
"""Prove two distinct native MUIFLI fields, physical pixels, cadence and no SID.

This is the primary native boundary for MUIFLI. NUFLI's static one-field proof
cannot detect swapped fields, stale relocated tail data or wrong interlace
cadence. Uses ordinary program entry/IRQ boundaries, with no code/PC writes.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import socket
import subprocess

from PIL import Image, ImageChops

from decode import decode_field, memory_image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUTPUT = HERE / "build/verification"


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fields", type=int, default=6)
    args = parser.parse_args()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    receipt = OUTPUT / ("receipt.json" if args.fields >= 6 else "trial-receipt.json")
    # A failed attempt must not leave either its own or the full-run success
    # looking current. Timestamped historical receipts are untouched.
    for destination in {OUTPUT / "receipt.json", receipt}:
        destination.unlink(missing_ok=True)
    shared = module("muifli_monitor", ROOT / "verify.py")
    mui = (HERE / "build/example.mui").read_bytes()
    program = (HERE / "build/example.prg").read_bytes()
    assert program[2 + 0x2100 - 0x0801:] == mui[2:]
    decoded = [decode_field(mui, field) for field in range(2)]
    assert decoded[0][0] != decoded[1][0]
    palette = [tuple(int(value, 16) for value in line.split())
               for line in (ROOT / "palettes/colodore.vpl").read_text().splitlines()
               if line and not line.startswith("#")]
    for field in range(2):
        image = Image.new("RGB", (320, 200))
        image.putdata([palette[color] for color in decoded[field][0]])
        image.save(OUTPUT / f"expected-{field}.png")
    with socket.socket() as reservation:
        reservation.bind(("127.0.0.1", 0))
        port = reservation.getsockname()[1]
    command = shared.vice_command(os.environ.get("VICE", "x64sc"), HERE / "build/example.prg", port,
                                  ROOT / "palettes/colodore.vpl")
    monitor = None
    with (OUTPUT / "vice.log").open("w") as log:
        process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT)
        try:
            with shared.connect_monitor(process, port) as connection:
                monitor = shared.Monitor(connection)
                monitor.run("r")
                def checkpoint(command):
                    return int(re.search(r"(?:BREAK|TRACE):\s+(\d+)", monitor.run(command))[1])

                start = checkpoint("break 3000")
                monitor.run("x")
                monitor.run("bank ram")
                loaded = monitor.memory(OUTPUT / "loaded-ram.bin", 0, 0xFFFF)
                monitor.run("bank cpu")
                assert loaded[0x0801:0xCD00] == program[2:]
                provenance = json.loads((HERE / "SOURCE.json").read_text())
                assert hashlib.sha256(loaded[0x3000:0x3300]).hexdigest() == provenance["player_arrays"]["muifli_displayer_code1"]
                assert hashlib.sha256(loaded[0xB000:0xB300]).hexdigest() == provenance["player_arrays"]["muifli_displayer_code2"]
                monitor.run(f"delete {start}")
                checkpoint("trace store 0001")
                checkpoint("trace store d400 d7ff")
                checkpoint("trace store dd00")
                checkpoint("break 32c8")
                checkpoint("break b2c8")
                records, images = [], []
                expected_ram = memory_image(mui)
                snapshots = module("muifli_snapshots", ROOT / "research/quondam/snapshot_state.py")
                cpu_port = loaded[1]
                ram_under_sid_stores = 0
                for sample in range(args.fields):
                    response = monitor.run("x")
                    pc, raster, clock = monitor.registers()
                    assert pc in (0x32C8, 0xB2C8), hex(pc)
                    field = 0 if pc == 0x32C8 else 1
                    assert field == sample % 2
                    # Let the unchanged IRQ return and finish the line. This
                    # executes normal instructions; it writes no PC or code.
                    response += monitor.run("z 200")
                    bank_events = []
                    bank_latch = None
                    for address, line, cycle, pc_store, accumulator, store_clock in re.findall(
                            r"Trace store ([0-9a-f]{4})\)\s+(\d+)/\$[0-9a-f]+,\s+(\d+)/\$[0-9a-f]+\n"
                            r".C:([0-9a-f]{4})[^\n]* A:([0-9a-f]{2})[^\n]*\s+(\d+)", response, re.I):
                        address, pc_store, accumulator = (int(v, 16) for v in (address, pc_store, accumulator))
                        if address == 1:
                            cpu_port = accumulator
                        elif 0xD400 <= address < 0xD800:
                            assert not (cpu_port & 4 and cpu_port & 3), "An I/O-mapped SID write occurred"
                            ram_under_sid_stores += 1
                        elif address == 0xDD00 and cpu_port & 4 and cpu_port & 3:
                            if pc_store in (0x322B, 0xB22B):
                                bank_latch = accumulator
                            else:
                                assert pc_store in (0x1A9D, 0x9A9D) and bank_latch is not None
                                bank_latch += 1
                            bank_events.append({"line": int(line), "cycle": int(cycle), "clock": int(store_clock),
                                                "pc": pc_store, "latch": bank_latch})
                    assert [(item["line"], item["latch"]) for item in bank_events] == [(42, 2 - 2 * field), (175, 3 - 2 * field)]
                    screenshot = OUTPUT / f"native-{sample:02d}-field-{field}.png"
                    monitor.run(f'scrsh "{screenshot}" 2')
                    image = Image.open(screenshot).convert("RGB")
                    expected = Image.new("RGB", image.size, palette[0])
                    # RC0 starts at48. Only the first cold field waits for
                    # the RSEL top comparison at51; the tail leaves the border
                    # open across subsequent wraps, exposing all200 rows.
                    # FineX1 places x0 at33; the side border hides x319.
                    source = Image.open(OUTPUT / f"expected-{field}.png")
                    top = 3 if sample == 0 else 0
                    expected.paste(source.crop((0, top, 319, 200)), (33, 32 + top))
                    difference = ImageChops.difference(image, expected)
                    if difference.getbbox() is not None:
                        difference.save(OUTPUT / "difference-failed.png")
                        expected.save(OUTPUT / "expected-full-failed.png")
                        wrong = [(i % image.width, i // image.width, a, b) for i, (a, b) in enumerate(zip(image.get_flattened_data(), expected.get_flattened_data())) if a != b]
                        (OUTPUT / "pixel-failure.json").write_text(json.dumps({"count": len(wrong), "first": wrong[:80]}, indent=2))
                        raise AssertionError((sample, field, len(wrong), "full native pixels"))
                    monitor.run("bank ram")
                    ram = monitor.memory(OUTPUT / f"ram-{sample:02d}.bin", 0, 0xFFFF)
                    monitor.run("bank cpu")
                    assert ram[0xCD00:0xF700] == expected_ram[0xCD00:0xF700], "Relocated picture tail changed"
                    for image_field in range(2):
                        offset = image_field * 0x8000
                        for first, end in ((0x6000, 0x7400), (0x3400, 0x3F40)):
                            assert ram[offset + first:offset + end] == expected_ram[offset + first:offset + end]
                        for y in range(0, 200, 2):
                            page = (0x4000 + (((~y >> 1) & 7) << 10) if y < 128 else
                                    0x2000 + ((((y >> 1) + (y >= 168)) & 3) << 10)) + offset
                            first = page + (y // 8) * 40
                            assert ram[first:first + 40] == expected_ram[first:first + 40]
                    snapshot = OUTPUT / f"native-{sample:02d}.vsf"
                    monitor.run(f'dump "{snapshot}"')
                    state = snapshots.read_snapshot(snapshot)
                    vic = state["vicii"]
                    assert vic["vborder"] == vic["set_vborder"] == 0
                    assert vic["regs"][0x16] & 31 == 9 and vic["regs"][0x15] == 0x7F
                    assert vic["regs"][0x1B] == vic["regs"][0x1D] == 255 and vic["regs"][0x1C] == 0
                    assert state["cia"]["CIA2"]["ddra"] & 3 == 3
                    assert state["cia"]["CIA2"]["pra"] & 3 == 3 - 2 * field
                    records.append({"sample": sample, "field": field, "raster": raster, "clock": clock,
                                    "screenshot": screenshot.name, "bank_events": bank_events,
                                    "cold_top_rows_clipped": top, "snapshot": snapshot.name,
                                    "ram_sha256": hashlib.sha256(ram).hexdigest()})
                    images.append(image)
                    print(f"Checked MUIFLI field {sample + 1}/{args.fields}", flush=True)
                intervals = [b["clock"] - a["clock"] for a, b in zip(records, records[1:])]
                assert not intervals or set(intervals) == {19656}
                assert ram_under_sid_stores == 1024
                controls = []
                for field in range(2):
                    controls.append({name: sum(a != b for a, b in zip(decoded[field][0], decode_field(mui, field, variant)[0]))
                                     for name, variant in (("without_bitmap", "no_bitmap"), ("without_six_underlays", "no_sprites"))})
                    assert all(value > 0 for value in controls[-1].values())
                pairs = list(zip(decoded[0][0], decoded[1][0]))
                means = [tuple((palette[a][channel] + palette[b][channel]) // 2 for channel in range(3)) for a, b in pairs]
                mean_image = Image.new("RGB", (320, 200))
                mean_image.putdata(means)
                mean_image.save(OUTPUT / "digital-mean.png")
                weave_image = Image.new("RGB", (320, 200))
                weave_image.putdata([palette[pair[index % 320 & 1]] for index, pair in enumerate(pairs)])
                weave_image.save(OUTPUT / "digital-column-weave.png")
                images[0].save(OUTPUT / "muifli-fields.gif", save_all=True, append_images=images[1:], duration=200, loop=0)
                result = {"pass": True, "fields": args.fields, "field_cadence_clocks": intervals,
                          "pixels_checked_each_field": image.width * image.height, "SID_stores": 0,
                          "RAM_relocation_stores_beneath_SID": ram_under_sid_stores,
                          "relocated_tail_bytes_checked_each_capture": 10752,
                          "bitmap_bytes_checked_each_capture": 16000,
                          "attribute_bytes_checked_each_capture": 8000,
                          "viewer_unchanged": True,
                          "different_field_pixel_positions": sum(a != b for a, b in pairs),
                          "distinct_physical_colors_per_field": [len(set(item[0])) for item in decoded],
                          "distinct_digital_mean_RGB_values": len(set(means)),
                          "independent_layer_omission_pixels": controls,
                          "decoded_layer_ownership": [item[1] for item in decoded], "records": records,
                          "command": command, "program_sha256": hashlib.sha256(program).hexdigest(),
                          "scope": "Own static MUIFLI artwork with unchanged attributed Mufflon viewer. Literal physical field colors and full native images, including cold first-field clipping. Mean/weave/GIF are inspection artifacts; no analog blending, new physical colors, NTSC or physical-hardware claim."}
                receipt.write_text(json.dumps(result, indent=2) + "\n")
                print(json.dumps({k: v for k, v in result.items() if k not in ("records", "command")}, indent=2))
        finally:
            if monitor:
                (OUTPUT / "monitor.log").write_text("\n".join(monitor.transcript))
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
            if "result" in locals():
                result["owned_process_closed"] = process.poll() is not None
                result["owned_process_returncode"] = process.returncode
                receipt.write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
