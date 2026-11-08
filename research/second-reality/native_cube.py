#!/usr/bin/env python3
"""Capture and audit original BA/BB cube fields through the owned VICE observer.

The capture resumes a complete original-machine snapshot. It changes no C64
code, RAM, registers or PC. Existing monitor breakpoints observe the return
from the final raster IRQ's SID call, while tracepoints retain descriptor/scanout
stores. The audit is passive and keeps restore differences explicit.
"""

import argparse
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

from PIL import Image, ImageDraw


sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "build/research/second-reality"
OBSERVER = ROOT / "research/vice_session_live.py"
spec = importlib.util.spec_from_file_location("cube_snapshot_reader", ROOT / "research/quondam/snapshot_state.py")
reader = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reader)
REGISTER = re.compile(r"^\.;([0-9a-f]{4})\s+([0-9a-f]{2})\s+([0-9a-f]{2})\s+([0-9a-f]{2})\s+"
                      r"([0-9a-f]{2})\s+([0-9a-f]{2})\s+([0-9a-f]{2})\s+([01]{8})\s+(\d+)\s+(\d+)\s+(\d+)", re.I)
TRACE = re.compile(r"^\.C:([0-9a-f]{4}).*? - A:([0-9a-f]{2}) X:([0-9a-f]{2}) Y:([0-9a-f]{2}) "
                   r"SP:([0-9a-f]{2}).*?\s(\d+)$", re.I)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def artifact(path):
    path = path.resolve()
    data = path.read_bytes()
    return {"path": str(path.relative_to(ROOT)), "bytes": len(data), "sha256": sha(data)}


def registers(text):
    matches = [REGISTER.match(line.strip()) for line in text.splitlines()]
    match = next((row for row in reversed(matches) if row), None)
    if match is None:
        raise AssertionError(("Missing complete native register row", text))
    values = match.groups()
    names = ("pc", "a", "x", "y", "sp", "port00", "port01")
    return {**{name: int(value, 16) for name, value in zip(names, values[:7])},
            "flags": int(values[7], 2), "raster_line": int(values[8]),
            "raster_cycle": int(values[9]), "clock": int(values[10])}


def snapshot_cpu(path):
    state = reader.read_snapshot(path)
    module = state["modules"]["MAINCPU"]
    assert module["version"] == [1, 4] and module["payload_size"] == 103
    data = reader.module_payload(path, "MAINCPU")
    return {"clock": int.from_bytes(data[:8], "little"), "a": data[8], "x": data[9], "y": data[10],
            "sp": data[11], "pc": int.from_bytes(data[12:14], "little"), "flags": data[14]}


def snapshot_ram(path):
    module = reader.read_snapshot(path)["modules"]["C64MEM"]
    assert module["version"] == [0, 1] and module["payload_size"] == 65555
    return reader.module_payload(path, "C64MEM")[4:65540]


class Observer:
    """One JSON client, one existing observer, one owned VICE process."""

    def __init__(self, disk, output):
        self.sequence = 0
        self.command = [sys.executable, str(OBSERVER), str(disk), "--disk", str(disk),
                        "--no-autostart", "--observation-timeout", "15", "--output", str(output)]
        self.process = subprocess.Popen(self.command, cwd=ROOT, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                        stderr=subprocess.STDOUT, text=True, bufsize=1)
        self.closed = None
        self.receive(lambda row: "ready" in row)

    def receive(self, predicate):
        while True:
            text = self.process.stdout.readline()
            if not text:
                raise RuntimeError("Owned observer closed before the requested response")
            row = json.loads(text)
            if predicate(row):
                return row

    def run(self, command):
        self.sequence += 1
        identity = f"cube-{self.sequence}"
        self.process.stdin.write(json.dumps({"command": command, "id": identity}) + "\n")
        self.process.stdin.flush()
        while True:
            row = self.receive(lambda value: value.get("id") == identity and value.get("status") in
                               ("completed", "partial", "interrupted"))
            if row["status"] == "partial":
                # Interrupt this exact pending command once. Never retry it or
                # restore the machine after an observation timeout.
                self.process.stdin.write(json.dumps({"interrupt": True}) + "\n")
                self.process.stdin.flush()
                self.receive(lambda value: value.get("id") == identity and value.get("status") == "interrupted")
                raise RuntimeError(("Native observation did not reach its breakpoint", command))
            assert row["status"] == "completed", row
            response = row["response"]
            assert not re.search(r"ERROR|Unknown command|Unknown resource|Syntax error", response), (command, response)
            return response

    def close(self):
        if self.process.poll() is not None:
            return
        self.process.stdin.write(json.dumps({"close": True}) + "\n")
        self.process.stdin.flush()
        self.closed = self.receive(lambda row: row.get("closed") is True)
        self.process.stdin.close()
        self.process.wait(timeout=15)
        assert self.closed["session"]["owned_process_reaped"] is True


def capture(args):
    source, disk, output = args.snapshot.resolve(), args.disk.resolve(), args.output.resolve()
    assert not output.exists(), "Use a fresh capture directory"
    assert source.is_file() and disk.is_file()
    ram = snapshot_ram(source)
    assert ram[8:10] == bytes.fromhex("00 3b"), "Steady full-size zoom snapshot required"
    assert ram[0x4060:0x4063] == bytes.fromhex("8d c1 40"), "Unexpected original BA IRQ entry"
    observer = Observer(disk, output)
    frames = []
    try:
        shutil.copy2(Path(__file__).resolve(), output / "producer-native_cube.py")
        (output / "capture-plan.json").write_text(json.dumps({
            "source": artifact(source), "disk": artifact(disk), "producer": artifact(Path(__file__)),
            "observer": artifact(OBSERVER), "fields": args.fields, "clock_domain": "Native PAL machine clocks",
            "normal_speed": 100, "warp_during_measurement": False,
            "stop": "Original $40eb after the final raster IRQ's SID call; visible rows have been scanned",
        }, indent=2) + "\n")
        observer.run(f'undump "{source}"')
        observer.run("r")
        observer.run("bank ram")
        observer.run(f'bsave "{output / "ram-restored-steady-cube.bin"}" 0 0000 ffff')
        observer.run(f'dump "{output / "restored-steady-cube.vsf"}"')
        observer.run("warp off")
        observer.run("trace exec 4f82")
        observer.run("trace exec 4f87")
        observer.run("trace exec 4f9f")
        observer.run("trace exec 4fa4")
        observer.run("trace store d018")
        observer.run("break 40eb")
        previous = None
        for index in range(args.fields):
            observer.run("x")
            reg = registers(observer.run("r"))
            assert reg["pc"] == 0x40EB and 250 <= reg["raster_line"] < 312
            if previous is not None:
                phase_delta = 63 * (reg["raster_line"] - previous["raster_line"]) + reg["raster_cycle"] - previous["raster_cycle"]
                assert reg["clock"] - previous["clock"] - phase_delta == 19656, (index, previous, reg)
            name = f"field-{index:03d}"
            observer.run(f'bsave "{output / ("ram-" + name + ".bin")}" 0 0000 ffff')
            observer.run(f'dump "{output / (name + ".vsf")}"')
            observer.run(f'screenshot "{output / (name + ".png")}" 2')
            actual = (output / ("ram-" + name + ".bin")).read_bytes()
            assert actual[8:10] == bytes.fromhex("00 3b"), (index, "Zoom changed")
            frames.append({"name": name, "registers": reg, "geometry_index": actual[0x02C0],
                           "texture_index": actual[0x02C1], "descriptor_406a": actual[0x406A],
                           "descriptor_4097": actual[0x4097], "color_matrices_sha256": sha(actual[0xC000:0xD000])})
            previous = reg
            if (index + 1) % 20 == 0:
                print(f"Captured {index + 1}/{args.fields} original cube PAL fields", flush=True)
        (output / "fields.json").write_text(json.dumps(frames, indent=2) + "\n")
    finally:
        observer.close()
    images = [Image.open(output / f"{row['name']}.png").convert("RGB") for row in frames]
    images[0].save(output / "original-cube-fields.gif", save_all=True, append_images=images[1:],
                   duration=20, loop=0, optimize=False)
    indices = list(range(0, len(images), max(1, len(images) // 16)))[:16]
    sheet = Image.new("RGB", (384 * 4, 292 * 4), "black")
    draw = ImageDraw.Draw(sheet)
    for tile, index in enumerate(indices):
        left, top = (tile % 4) * 384, (tile // 4) * 292
        sheet.paste(images[index], (left, top))
        draw.text((left + 8, top + 274), f"field {index}, pose {frames[index]['geometry_index']}, texture {frames[index]['texture_index']}", fill="white")
    sheet.save(output / "contact-sheet.png")
    print(json.dumps({"capture": str(output.relative_to(ROOT)), "fields": len(frames),
                      "first_clock": frames[0]["registers"]["clock"], "last_clock": frames[-1]["registers"]["clock"]}, indent=2))


def audit(directory, allow_open=False):
    directory = directory.resolve()
    session = json.loads((directory / "session.json").read_text())
    assert session.get("closed_utc") or allow_open, "Final evidence requires a closed owned session"
    events = [json.loads(line) for line in (directory / "events.jsonl").read_text().splitlines()]
    wire = (directory / "received.bin").read_bytes()
    responses = [row for row in events if row["kind"] == "response"]
    current, captures, restores, rejected = None, {}, [], []
    for row in responses:
        command, response = row["command"], row["response"]
        assert wire[row["received_first"]:row["received_end"]].decode(errors="replace") == response
        if row["status"] != "completed":
            raise AssertionError(("Interrupted capture observation is not a successful breakpoint", row))
        if command == "r":
            current = registers(response)
            continue
        if command == "x":
            current = None
            continue
        match = re.fullmatch(r'undump "([^"\n]+)"', command)
        if match:
            restores.append(artifact(Path(match[1])))
            current = None
            continue
        match = re.fullmatch(r'(bsave|dump|screenshot) "([^"\n]+)"(.*)', command)
        if match:
            kind, filename, suffix = match.groups()
            path = Path(filename).resolve()
            assert path.parent == directory and current is not None, (command, current)
            assert suffix == {"bsave": " 0 0000 ffff", "dump": "", "screenshot": " 2"}[kind]
            captures[path.name] = {"artifact": artifact(path), "registers": dict(current), "kind": kind}
            continue
        if re.search(r"ERROR|Unknown resource|Syntax error", response):
            assert command.startswith("resourceset "), (command, response)
            rejected.append({"command": command, "response": response})
            continue
        safe = (command in ("sidefx off", "bank ram", "warp on", "warp off")
                or re.fullmatch(r'(?:break|trace|delete|ignore|d|help) [^\n]+', command)
                or re.fullmatch(r'attach "[^"\n]+/2ND2\.D64" 8', command))
        assert safe, ("Unapproved observation or machine intervention", command)
    assert len(restores) == 1, restores
    pairs = []
    for name, item in captures.items():
        if item["kind"] != "dump":
            continue
        stem = Path(name).stem
        snapshot, ram_path = directory / name, directory / f"ram-{stem}.bin"
        assert ram_path.name in captures, (stem, "Missing full RAM capture")
        reg = item["registers"]
        assert captures[ram_path.name]["registers"] == reg
        data = ram_path.read_bytes()
        assert len(data) == 65536 and data == snapshot_ram(snapshot), (stem, "RAM/VSF mismatch")
        assert all(snapshot_cpu(snapshot)[key] == value for key, value in reg.items()
                   if key in snapshot_cpu(snapshot)), (stem, "CPU/VSF mismatch")
        vic = reader.read_snapshot(snapshot)["vicii"]
        assert [vic["raster_line"], vic["raster_cycle"]] == [reg["raster_line"], reg["raster_cycle"]]
        if stem + ".png" in captures:
            assert captures[stem + ".png"]["registers"] == reg
        pairs.append({"name": stem, "ram": captures[ram_path.name]["artifact"], "snapshot": item["artifact"], "registers": reg})
    assert pairs
    restored = next(row for row in pairs if row["name"].startswith("restored-"))
    comparison = reader.compare_modules(ROOT / restores[0]["path"], ROOT / restored["snapshot"]["path"])
    for module in ("MAINCPU", "C64MEM", "CIA1", "CIA2", "VIC-II"):
        assert reader.module_payload(ROOT / restores[0]["path"], module) == reader.module_payload(ROOT / restored["snapshot"]["path"], module)
    trace_rows = []
    for line in wire.decode(errors="replace").splitlines():
        match = TRACE.match(line)
        if match:
            trace_rows.append({"pc": int(match[1], 16), "a": int(match[2], 16), "x": int(match[3], 16),
                               "y": int(match[4], 16), "sp": int(match[5], 16), "clock": int(match[6])})
    publication_rows = [row for row in trace_rows if row["pc"] in (0x4F87, 0x4FA4)]
    intervals = [b["clock"] - a["clock"] for a, b in zip(publication_rows, publication_rows[1:])]
    report = {"pass": bool(session.get("closed_utc")), "session": session, "source_snapshot": restores[0],
              "snapshot_restore_comparison": comparison, "C64_modules_restored_exactly": ["MAINCPU", "C64MEM", "CIA1", "CIA2", "VIC-II"],
              "whole_machine_restore_identity": comparison["all_module_payloads_equal"],
              "RAM_snapshot_pairs": pairs, "total_RAM_bytes_compared": len(pairs) * 65536,
              "captures": captures, "rejected_resource_commands": rejected,
              "direct_RAM_writes": [], "register_or_PC_writes": [], "trace_rows": trace_rows,
              "descriptor_second_store_observations": publication_rows,
              "descriptor_store_interval_PAL_clocks": intervals,
              "descriptor_store_mean_updates_per_second": None if not intervals else 985248 / (sum(intervals) / len(intervals)),
              "scope": "Original output observations, exact CPU/beam/RAM capture integrity and explicit full-snapshot restore lineage. Descriptor-store cadence is not a claim of frame-coherent publication; actual D018 traces and field images remain available for that analysis.",
              "wire": artifact(directory / "received.bin"), "events": artifact(directory / "events.jsonl"),
              "observer_source": artifact(OBSERVER), "snapshot_reader_source": artifact(ROOT / "research/quondam/snapshot_state.py"),
              "auditor_source": artifact(Path(__file__))}
    (directory / "native-cube-evidence.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"capture": str(directory.relative_to(ROOT)), "pass": report["pass"], "RAM_pairs": len(pairs),
                      "descriptor_second_stores": len(publication_rows), "descriptor_store_updates_per_second": report["descriptor_store_mean_updates_per_second"],
                      "whole_machine_restore_identity": report["whole_machine_restore_identity"]}, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="mode", required=True)
    live = sub.add_parser("capture", help="Resume an original full-size cube snapshot and retain consecutive native PAL fields")
    live.add_argument("--snapshot", type=Path, required=True)
    live.add_argument("--disk", type=Path, default=BASE / "csdb-2ndreality-members/2ND2.D64")
    live.add_argument("--output", type=Path, required=True)
    live.add_argument("--fields", type=int, default=160)
    passive = sub.add_parser("audit", help="Audit retained capture journals and original-machine snapshots; starts no emulator")
    passive.add_argument("directories", type=Path, nargs="+")
    passive.add_argument("--allow-open-session", action="store_true")
    args = parser.parse_args()
    if args.mode == "capture":
        assert args.fields > 1
        capture(args)
    else:
        for directory in args.directories:
            audit(directory, args.allow_open_session)


if __name__ == "__main__":
    main()
