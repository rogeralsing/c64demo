#!/usr/bin/env python3
"""Run real D64/1541 loads and verify slot ownership, music progress and viewports."""

from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import re
import shutil
import socket
import subprocess

from PIL import Image, ImageChops


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
spec = importlib.util.spec_from_file_location("cube_verification", ROOT / "verify.py")
common = importlib.util.module_from_spec(spec)
spec.loader.exec_module(common)
SLOTS = (0x8000, 0x8800, 0x9000, 0x9800)
MID_LOADS = {0, 4, 12, 19}
INK = (6, 4, 2, 8, 5, 3, 14, 4)
PAPER = (14, 10, 8, 7, 13, 1, 1, 10)
BORDER = (6, 4, 3, 14, 3, 4, 6, 0)


def byte(ram, labels, name):
    return ram[labels[name]]


def word(ram, labels, name):
    return byte(ram, labels, name) | ram[labels[name] + 1] << 8


def read_registers(monitor):
    response = monitor.run("r")
    match = re.search(r"^\.;([0-9a-fA-F]{4})\s+(.*)$", response, re.M)
    if not match:
        raise RuntimeError("No native register response.")
    values = match[2].split()
    return {"pc": int(match[1], 16), "a": int(values[0], 16),
            "x": int(values[1], 16), "y": int(values[2], 16),
            "carry": int(values[6][-1]), "raster": int(values[-3]),
            "clock": int(values[-1])}


def art(x, y):
    """Independent pixel sampler for the original mathematical artwork."""
    ridge = math.floor(96 + 28 * math.sin(x * math.tau / 180)
                       + 15 * math.sin(x * math.tau / 61) + 0.5)
    if y < ridge - 14:
        selector = int(y < 80 and (17 * x + 29 * y) % 257 == 0) * 3
    elif y < ridge:
        selector = 1 + int(y % 4 < 2)
    else:
        selector = 1 + (x // 6 + y // 5) % 3
    index = ((x // 4) // 8 + (y // 8) // 3) % 8
    return selector, INK[index] * 16 + PAPER[index], 1


def payload(physical_x, physical_width):
    columns = physical_width // 8
    bitmap = bytearray(columns * 25 * 8)
    screen, colors = bytearray(columns * 25), bytearray(columns * 25)
    for y in range(200):
        for local_x in range(physical_width // 2):
            selector, attributes, color = art(physical_x // 2 + local_x, y)
            cell = (y // 8) * columns + local_x // 4
            bitmap[cell * 8 + y % 8] |= selector << (6 - 2 * (local_x % 4))
            screen[cell] = attributes
            colors[cell] = color
    return bytes(bitmap + screen + colors)


def panorama_image(physical_x, palette):
    image = Image.new("RGB", (320, 200))
    pixels = []
    for y in range(200):
        for x in range(160):
            selector, attributes, color = art(physical_x // 2 + x, y)
            index = (0, attributes >> 4, attributes & 15, color)[selector]
            pixels.extend([palette[index], palette[index]])
    image.putdata(pixels)
    return image


def crop_native(image, expected):
    for x, y in [(32, 35)] + [(x, y) for y in range(30, 41) for x in range(28, 37)
                             if (x, y) != (32, 35)]:
        crop = image.crop((x, y, x + 320, y + 200))
        if ImageChops.difference(crop, expected).getbbox() is None:
            return crop, [x, y]
    raise AssertionError("Native screen differs from independently sampled panorama/text pixels.")


def check_guards(ram):
    for base in SLOTS:
        if ram[base + 2000:base + 2048] != bytes([0xcc]) * 48:
            raise AssertionError(f"Resident slot guard changed after its 2,000-byte payload at ${base:04x}.")


def check_slots(ram, labels, states, ids):
    if list(ram[labels["slotStates"]:labels["slotStates"] + 4]) != states:
        raise AssertionError("Native slot ownership differs from the producer/consumer model.")
    if list(ram[labels["slotIds"]:labels["slotIds"] + 4]) != ids:
        raise AssertionError("Native slot identities differ from ordered disk loading.")
    check_guards(ram)


def capture_view(monitor, ram, labels, consumed, output, prefix, palette):
    expected = payload(consumed * 64, 320)
    bitmap, screen = ((0x2000, 0x0400) if consumed % 2 == 0 else (0x6000, 0x5c00))
    if ram[bitmap:bitmap + 8000] != expected[:8000]:
        differing = sum(a != b for a, b in zip(ram[bitmap:bitmap + 8000], expected[:8000]))
        raise AssertionError(f"Viewport {consumed} differs in {differing} bitmap bytes.")
    if ram[screen:screen + 1000] != expected[8000:9000]:
        raise AssertionError("Viewport screen attributes differ from the source coordinates.")
    if byte(ram, labels, "frontBitmapHi") << 8 != bitmap or byte(ram, labels, "frontScreenHi") << 8 != screen:
        raise AssertionError("Published front-buffer metadata disagrees with the expected viewport.")
    monitor.run("bank io")
    vic = monitor.memory(output / f"{prefix}-vic.bin", 0xd000, 0xd03f)
    cia = monitor.memory(output / f"{prefix}-cia.bin", 0xdd00, 0xdd03)
    colors = monitor.memory(output / f"{prefix}-colors.bin", 0xd800, 0xdbe7)
    if bytes(value & 15 for value in colors) != expected[9000:10000]:
        raise AssertionError("Color RAM stream does not match the independent viewport.")
    if vic[0x11] & 0x7f != 0x3b or vic[0x16] & 0x3f != 0x18:
        raise AssertionError("The current image left multicolor bitmap mode.")
    expected_d018 = 0x18 if consumed % 2 == 0 else 0x78
    expected_bank = 3 if consumed % 2 == 0 else 2
    if vic[0x18] & 0xfe != expected_d018 or cia[0] & 3 != expected_bank or cia[2] & 3 != 3:
        raise AssertionError("Actual VIC bank/screen/bitmap does not select the completed image.")
    if vic[0x15] or vic[0x21] & 15:
        raise AssertionError("Sprites or a changed background affect the panorama.")
    music = word(ram, labels, "musicCounter")
    if music and vic[0x20] & 15 != BORDER[(music >> 3) % 8]:
        raise AssertionError("The independent IRQ border animation stopped matching its music counter.")
    monitor.run("bank cpu")
    screenshot = output / f"{prefix}.png"
    monitor.run(f'screenshot "{screenshot}" 2')
    expected_image = panorama_image(consumed * 64, palette)
    crop, origin = crop_native(Image.open(screenshot).convert("RGB"), expected_image)
    crop.save(output / f"{prefix}-crop.png")
    expected_image.save(output / f"{prefix}-expected.png")
    return {"consumed_strips": consumed, "source_x": consumed * 64,
            "bitmap_bytes_checked": 8000, "screen_bytes_checked": 1000,
            "color_bytes_checked": 1000, "native_pixels_checked": 64000,
            "screenshot": screenshot.name, "origin": origin,
            "music_counter": music, "border_color": vic[0x20] & 15}, crop


def final_image(matrix, chargen, palette):
    image = Image.new("RGB", (320, 200))
    image.putdata([palette[1 if chargen[matrix[(y // 8) * 40 + x // 8] * 8 + y % 8]
                           & (128 >> (x % 8)) else 0]
                   for y in range(200) for x in range(320)])
    return image


def final_matrix():
    matrix = bytearray([32]) * 1000
    matrix[412:427] = bytes((19,20,18,5,1,13,32,3,15,13,16,12,5,20,5))
    matrix[492:508] = bytes((50,48,32,19,20,18,9,16,19,32,12,15,1,4,5,4))
    return matrix


def main():
    labels = common.read_labels(HERE / "build/main.sym")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    output = HERE / "build/verification" / stamp
    output.mkdir(parents=True)
    program, disk = output / "program.prg", output / "stream.d64"
    shutil.copy2(HERE / "build/example.prg", program)
    shutil.copy2(HERE / "build/example.d64", disk)
    shutil.copy2(HERE / "build/manifest.json", output / "manifest.json")
    disk_hash = hashlib.sha256(disk.read_bytes()).hexdigest()
    palette_path = ROOT / "palettes/colodore.vpl"
    palette = [tuple(int(value, 16) for value in line.split()[:3])
               for line in palette_path.read_text().splitlines()
               if line.strip() and not line.lstrip().startswith("#")]
    executable = shutil.which("x64sc")
    chargen_path = Path(executable).resolve().parents[1] / "share/vice/C64/chargen-901225-01.bin"
    if not chargen_path.is_file():
        chargen_path = Path("/opt/homebrew/share/vice/C64/chargen-901225-01.bin")
    chargen = chargen_path.read_bytes()
    with socket.socket() as reserve:
        reserve.bind(("127.0.0.1", 0))
        port = reserve.getsockname()[1]
    command = common.vice_command(executable, program, port, palette_path)
    command.extend(["-drive8truedrive", "+trapdevice8", "-8", str(disk), "-chargen", str(chargen_path)])
    report = {"pass": False, "program_sha256": hashlib.sha256(program.read_bytes()).hexdigest(),
              "disk_sha256": disk_hash, "vice_command": command,
              "chargen_sha256": hashlib.sha256(chargen).hexdigest(),
              "loader": "C64 KERNAL IEC LOAD; true 1541 drive; device-8 traps disabled",
              "memory_or_pc_writes": False, "loads": [], "views": [], "events": []}
    states, ids = [0] * 4, [255] * 4
    loaded, consumed, released, active, consuming = 0, 0, 0, None, None
    process = monitor = None
    animation, animation_clocks = [], []
    finished = False
    text_publication = None
    try:
        with (output / "vice.log").open("w") as log:
            process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            with common.connect_monitor(process, port) as connection:
                monitor = common.Monitor(connection)
                connection.settimeout(45)
                monitor.run("r")
                monitor.run("sidefx off")
                names = ("loadStarted", "loadReturned", "loadComplete", "consumeBegin",
                         "stripPresented", "slotReleased", "textPublished", "finalScene", "fault", "irq")
                checkpoints = {}
                for name in names:
                    response = monitor.run(f"break {labels[name]:04x}")
                    checkpoints[name] = int(re.search(r"BREAK: (\d+)", response)[1])
                monitor.run(f"disable {checkpoints['irq']}")
                by_pc = {labels[name]: name for name in names}
                for event_index in range(180):
                    monitor.run("x")
                    registers = read_registers(monitor)
                    name = by_pc.get(registers["pc"])
                    if name is None:
                        raise AssertionError(f"Unexpected stop at ${registers['pc']:04x}.")
                    monitor.run("bank ram")
                    ram = monitor.memory(output / f"ram-{event_index:03d}-{name}.bin", 0, 0xffff)
                    monitor.run("bank cpu")
                    event = {"event": name, "clock": registers["clock"], "raster": registers["raster"],
                             "music": word(ram, labels, "musicCounter"),
                             "slot_states": list(ram[labels["slotStates"]:labels["slotStates"] + 4])}
                    report["events"].append(event)
                    if name == "fault":
                        raise AssertionError(f"C64 entered its loader/ownership fault ${byte(ram, labels, 'errorCode'):02x}.")
                    if name == "loadStarted":
                        strip = byte(ram, labels, "loadedStripId")
                        slot = strip % 4
                        if strip != loaded or states[slot] != 0 or active is not None:
                            raise AssertionError("Producer attempted an out-of-order load or overwrote an owned slot.")
                        states[slot] = 1
                        check_slots(ram, labels, states, ids)
                        old_payload = bytes([0xcc]) * 2000 if strip < 4 else payload(320 + (strip - 4) * 64, 64)
                        if ram[SLOTS[slot]:SLOTS[slot] + 2000] != old_payload:
                            raise AssertionError("Free slot changed before its actual disk load.")
                        if (registers["a"], registers["x"], registers["y"]) != (0, 0, SLOTS[slot] >> 8):
                            raise AssertionError("KERNAL LOAD did not receive the expected relocatable slot target.")
                        if ram[labels["filename"]:labels["filename"] + 2] != f"{strip:02d}".encode():
                            raise AssertionError("Wrong strip filename was passed to SETNAM.")
                        active = {"strip": strip, "slot": slot, "start_clock": registers["clock"],
                                  "start_music": event["music"], "start_irq": word(ram, labels, "irqDuringLoad"),
                                  "before": ram}
                        if strip in MID_LOADS:
                            target = (event["music"] + 64) % 256
                            monitor.run(f"condition {checkpoints['irq']} if (@ram:${labels['musicCounter']:04x} == ${target:02x}) && (@ram:${labels['loadActive']:04x} == $01)")
                            monitor.run(f"enable {checkpoints['irq']}")
                        print(f"Loading actual D64 strip {strip:02d} into slot {slot}", flush=True)
                    elif name == "irq":
                        monitor.run(f"disable {checkpoints['irq']}")
                        if active is None or byte(ram, labels, "loadActive") != 1:
                            raise AssertionError("The mid-load IRQ witness occurred outside actual LOAD execution.")
                        check_slots(ram, labels, states, ids)
                        if (event["music"] - active["start_music"]) % 65536 < 64:
                            raise AssertionError("Mid-load witness did not include sixty-four live music calls.")
                        view, _ = capture_view(monitor, ram, labels, consumed, output,
                                               f"during-load-{active['strip']:02d}", palette)
                        view["actual_load_in_progress"] = active["strip"]
                        report["views"].append(view)
                    elif name == "loadReturned":
                        if active is None or registers["carry"]:
                            raise AssertionError("KERNAL LOAD returned an error or no load was active.")
                        strip, slot = active["strip"], active["slot"]
                        if registers["x"] | registers["y"] << 8 != SLOTS[slot] + 2000:
                            raise AssertionError("KERNAL LOAD returned a wrong end address.")
                        check_slots(ram, labels, states, ids)
                        expected = payload(320 + strip * 64, 64)
                        if ram[SLOTS[slot]:SLOTS[slot] + 2000] != expected:
                            raise AssertionError("Actually loaded strip bytes differ from independent artwork indexing.")
                        for other, base in enumerate(SLOTS):
                            if other != slot and ram[base:base + 2048] != active["before"][base:base + 2048]:
                                raise AssertionError("A disk load changed another resident slot.")
                        calls = (event["music"] - active["start_music"]) % 65536
                        irq_calls = (word(ram, labels, "irqDuringLoad") - active["start_irq"]) % 65536
                        if calls == 0 or calls != irq_calls:
                            raise AssertionError("Music IRQ did not progress during the actual disk load.")
                        active.update({"elapsed_pal_clocks": registers["clock"] - active["start_clock"],
                                       "music_calls_during_load": calls,
                                       "payload_sha256": hashlib.sha256(expected).hexdigest()})
                        if strip == 0:
                            view, _ = capture_view(monitor, ram, labels, 0, output, "initial-viewport", palette)
                            report["views"].append(view)
                    elif name == "loadComplete":
                        if active is None:
                            raise AssertionError("Slot publication has no completed disk load.")
                        strip, slot = active["strip"], active["slot"]
                        states[slot], ids[slot] = 2, strip
                        check_slots(ram, labels, states, ids)
                        if byte(ram, labels, "loadActive") or word(ram, labels, "loadedEnd") != SLOTS[slot] + 2000:
                            raise AssertionError("Ready-slot publication precedes completed loader metadata.")
                        report["loads"].append({key: value for key, value in active.items() if key != "before"})
                        print(f"Loaded strip {strip:02d}: {active['music_calls_during_load']} music calls during disk I/O", flush=True)
                        active = None
                        loaded += 1
                    elif name == "consumeBegin":
                        slot = consumed % 4
                        if states[slot] != 2 or ids[slot] != consumed or byte(ram, labels, "currentSlot") != slot:
                            raise AssertionError("Consumer did not take the oldest ready strip.")
                        states[slot] = 3
                        check_slots(ram, labels, states, ids)
                        if event["music"] < word(ram, labels, "musicTarget"):
                            raise AssertionError("Viewport copy began before the real music-counter handshake.")
                        consuming = consumed
                    elif name == "stripPresented":
                        if consuming != consumed or byte(ram, labels, "consumedCount") != consumed + 1:
                            raise AssertionError("Viewport publication skipped or reordered a strip.")
                        check_slots(ram, labels, states, ids)
                        if not 256 <= registers["raster"] <= 260:
                            raise AssertionError("Published viewport was sampled before full scanout.")
                        view, image = capture_view(monitor, ram, labels, consumed + 1, output,
                                                   f"viewport-{consumed + 1:02d}", palette)
                        report["views"].append(view)
                        animation.append(image.resize((640, 400), Image.Resampling.NEAREST))
                        animation_clocks.append(registers["clock"])
                        consumed += 1
                        print(f"Verified complete native viewport {consumed}/20", flush=True)
                    elif name == "slotReleased":
                        slot = released % 4
                        if consuming != released or states[slot] != 3 or consumed != released + 1:
                            raise AssertionError("A slot was released before its viewport consumer completed.")
                        states[slot] = 0
                        check_slots(ram, labels, states, ids)
                        consuming = None
                        released += 1
                    elif name == "textPublished":
                        monitor.run(f"disable {checkpoints['textPublished']}")
                        if not 0 <= registers["raster"] <= 4:
                            raise AssertionError("Text mode was published outside the top-border window.")
                        if ram[0x5c00:0x5fe8] != final_matrix() or ram[0x4000:0x4800] != chargen[:2048]:
                            raise AssertionError("Text matrix/font was not fully prepared before publication.")
                        text_publication = registers["clock"]
                    elif name == "finalScene":
                        check_slots(ram, labels, states, ids)
                        if (loaded, consumed, released) != (20, 20, 20) or states != [0] * 4 or byte(ram, labels, "stage") != 2:
                            raise AssertionError("Final transition happened before all twenty strips were safely released.")
                        if (text_publication is None or registers["pc"] != labels["firstTextFieldComplete"]
                                or not 256 <= registers["raster"] <= 260
                                or not 0 < registers["clock"] - text_publication < 19656):
                            raise AssertionError("Final screenshot does not cover the first complete published text field.")
                        expected_matrix = final_matrix()
                        if ram[0x5c00:0x5fe8] != expected_matrix or ram[0x4000:0x4800] != chargen[:2048]:
                            raise AssertionError("Final scene text matrix differs from the planned handover.")
                        monitor.run("bank io")
                        vic = monitor.memory(output / "final-vic.bin", 0xd000, 0xd03f)
                        colors = monitor.memory(output / "final-colors.bin", 0xd800, 0xdbe7)
                        if vic[0x11] & 0x7f != 0x1b or vic[0x16] & 0x3f != 8 or vic[0x18] & 0xfe != 0x70:
                            raise AssertionError("Final scene did not switch to its intended text display.")
                        if bytes(value & 15 for value in colors) != bytes([1]) * 1000:
                            raise AssertionError("Final scene text colors differ.")
                        monitor.run("bank cpu")
                        screenshot = output / "final-scene.png"
                        monitor.run(f'screenshot "{screenshot}" 2')
                        expected_image = final_image(expected_matrix, chargen, palette)
                        image, origin = crop_native(Image.open(screenshot).convert("RGB"), expected_image)
                        image.save(output / "final-scene-crop.png")
                        expected_image.save(output / "final-scene-expected.png")
                        report["final_scene"] = {"native_pixels_checked": 64000, "origin": origin,
                                                 "screenshot": screenshot.name, "music_counter": event["music"],
                                                 "first_complete_text_field": True,
                                                 "publication_to_field_complete_clocks": registers["clock"] - text_publication}
                        animation.append(image.resize((640, 400), Image.Resampling.NEAREST))
                        animation_clocks.append(registers["clock"])
                        finished = True
                        break
                if not finished:
                    raise AssertionError("The bounded event run did not reach the final scene.")
        if hashlib.sha256(disk.read_bytes()).hexdigest() != disk_hash:
            raise AssertionError("The source D64 changed during its read-only loading run.")
        intervals = [second - first for first, second in zip(animation_clocks, animation_clocks[1:])]
        durations = [max(20, round(interval / 19656 * 20)) for interval in intervals] + [2000]
        animation[0].save(output / "animation.gif", save_all=True, append_images=animation[1:],
                          duration=durations, loop=0, optimize=False, disposal=2)
        report.update({"pass": True, "actual_strip_loads": loaded, "strips_consumed": consumed,
                       "payload_bytes_loaded": loaded * 2000, "maximum_resident_payload_bytes": 8000,
                       "resident_slot_bytes": 8192, "native_panorama_images_checked": len(report["views"]),
                       "bitmap_bytes_checked": len(report["views"]) * 8000,
                       "native_pixels_checked": (len(report["views"]) + 1) * 64000,
                       "mid_load_irq_captures": len(MID_LOADS), "animation": "animation.gif",
                       "load_clock_range": [min(row["elapsed_pal_clocks"] for row in report["loads"]),
                                             max(row["elapsed_pal_clocks"] for row in report["loads"])],
                       "music_calls_per_load_range": [min(row["music_calls_during_load"] for row in report["loads"]),
                                                       max(row["music_calls_during_load"] for row in report["loads"])],
                       "limits": ["coarse 64-pixel steps and real IEC loading pauses",
                                  "KERNAL timing suppresses some raster/music calls; no gap-free or 50 Hz music claim",
                                  "new educational scene, not Sparkle or an original No Bounds reconstruction",
                                  "bounded PAL VICE true-drive validation; no physical-drive margin claim"]})
    except Exception as error:
        report["error"] = str(error)
        raise
    finally:
        if monitor is not None:
            (output / "monitor.log").write_text("\n".join(monitor.transcript))
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        (output / "verification.json").write_text(json.dumps(report, indent=2) + "\n")
        print(f"Verification: {output / 'verification.json'}", flush=True)


if __name__ == "__main__":
    main()
